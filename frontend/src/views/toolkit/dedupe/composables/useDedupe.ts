import { ref, computed, triggerRef } from 'vue'
import { toolkitApi } from '@/api/toolkit'
import { useNotification } from '@/composables'

export function useDedupe() {
  const { success, error: showError, info } = useNotification()

  const loading = ref(false)
  const syncing = ref(false)
  const analyzing = ref(false)
  const searchName = ref('')
  const showOnlyDuplicates = ref(false)
  const items = ref<any[]>([])
  const selectedIds = ref<string[]>([])
  const suggestedItems = ref<any[]>([])

  // 分页 — 前端虚拟分页，避免一次性渲染大量 DOM
  const currentPage = ref(1)
  const pageSize = ref(50)

  // 配置
  const dedupeConfig = ref<any>({
    rules: { priority_order: [], values_weight: {}, tie_breaker: 'small_id' },
    exclude_paths: [],
  })

  // === 分页后的数据 ===
  const totalPages = computed(() => Math.ceil(items.value.length / pageSize.value) || 1)
  const pagedItems = computed(() => {
    const start = (currentPage.value - 1) * pageSize.value
    return items.value.slice(start, start + pageSize.value)
  })

  function processItems(data: any[]) {
    return data.map((i: any) => ({
      ...i,
      isLeaf: i.item_type !== 'Series' && i.item_type !== 'Season',
      expanded: false,
      children: [] as any[],
      childrenLoaded: false,
    }))
  }

  // === 加载列表 ===
  async function loadItems() {
    loading.value = true
    selectedIds.value = []
    currentPage.value = 1
    try {
      const data = await toolkitApi.dedupe.getItems({ query_text: searchName.value })
      items.value = processItems(Array.isArray(data) ? data : [])
    } catch {
      items.value = []
      showError('加载列表失败')
    } finally {
      loading.value = false
    }
  }

  // === 展开子项（按需加载 Season/Episode）===
  async function loadChildren(row: any) {
    if (row.childrenLoaded) {
      row.expanded = !row.expanded
      triggerRef(items)
      return
    }
    try {
      const data = await toolkitApi.dedupe.getItems({ parent_id: row.id })
      const children = processItems(Array.isArray(data) ? data : [])
      // 直接赋值并触发响应式更新
      row.children = children
      row.childrenLoaded = true
      row.expanded = true
      triggerRef(items)
    } catch {
      showError('加载子项失败')
    }
  }

  // === 切换重复项模式 ===
  async function toggleDuplicateMode() {
    showOnlyDuplicates.value = !showOnlyDuplicates.value
    if (showOnlyDuplicates.value) {
      loading.value = true
      selectedIds.value = []
      currentPage.value = 1
      try {
        const data = await toolkitApi.dedupe.getDuplicates()
        items.value = processItems(Array.isArray(data) ? data : [])
      } catch {
        items.value = []
        showError('加载重复项失败')
      } finally {
        loading.value = false
      }
    } else {
      loadItems()
    }
  }

  // === 同步媒体库 ===
  async function syncMedia() {
    if (syncing.value) return
    try {
      syncing.value = true
      info('同步任务已在后台启动，完成后将自动刷新列表')
      await toolkitApi.dedupe.syncMedia()
      const poll = setInterval(async () => {
        try {
          const status: any = await toolkitApi.dedupe.getSyncStatus()
          if (!status?.is_syncing) {
            clearInterval(poll)
            syncing.value = false
            success('Emby 媒体库同步已完成，列表已自动刷新')
            showOnlyDuplicates.value ? toggleDuplicateMode() : loadItems()
          }
        } catch {
          clearInterval(poll)
          syncing.value = false
        }
      }, 2000)
    } catch {
      syncing.value = false
      showError('启动同步任务失败')
    }
  }

  // === 智能选中 ===
  async function autoSelect() {
    analyzing.value = true
    try {
      const data = await toolkitApi.dedupe.smartSelect()
      const results = Array.isArray(data) ? data : []
      suggestedItems.value = results
      selectedIds.value = results.map((i: any) => i.id)
      if (results.length === 0) info('未发现符合规则的可清理项目')
      return results
    } catch {
      suggestedItems.value = []
      showError('算法执行失败')
      return []
    } finally {
      analyzing.value = false
    }
  }

  // === 删除 ===
  async function deleteItems(ids: string[]) {
    try {
      const res: any = await toolkitApi.dedupe.deleteItems(ids)
      success(`成功删除 ${res?.success ?? ids.length} 个项目`)
      selectedIds.value = []
      suggestedItems.value = []
      showOnlyDuplicates.value ? toggleDuplicateMode() : loadItems()
      return true
    } catch {
      showError('删除失败')
      return false
    }
  }

  // === 配置 ===
  async function loadConfig() {
    try {
      const data: any = await toolkitApi.dedupe.getConfig()
      if (data?.rules) dedupeConfig.value = data
    } catch { /* ignore */ }
  }

  async function saveConfig(config: any) {
    try {
      await toolkitApi.dedupe.saveConfig(config)
      dedupeConfig.value = config
      success('规则已保存')
      return true
    } catch {
      showError('保存配置失败')
      return false
    }
  }

  // === 工具 ===
  function toggleSelect(id: string) {
    const idx = selectedIds.value.indexOf(id)
    if (idx >= 0) selectedIds.value.splice(idx, 1)
    else selectedIds.value.push(id)
  }

  function selectAllPage() {
    const pageIds = pagedItems.value.map((i: any) => i.id)
    const allSelected = pageIds.every((id: string) => selectedIds.value.includes(id))
    if (allSelected) {
      selectedIds.value = selectedIds.value.filter((id: string) => !pageIds.includes(id))
    } else {
      pageIds.forEach((id: string) => {
        if (!selectedIds.value.includes(id)) selectedIds.value.push(id)
      })
    }
  }

  const confirmItems = computed(() => {
    if (suggestedItems.value.length > 0) {
      return suggestedItems.value.filter((i: any) => selectedIds.value.includes(i.id))
    }
    return items.value.filter((i: any) => selectedIds.value.includes(i.id))
  })

  return {
    loading, syncing, analyzing, searchName, showOnlyDuplicates,
    items, selectedIds, suggestedItems, dedupeConfig,
    currentPage, pageSize, totalPages, pagedItems, confirmItems,
    loadItems, loadChildren, toggleDuplicateMode, syncMedia,
    autoSelect, deleteItems, loadConfig, saveConfig,
    toggleSelect, selectAllPage,
  }
}
