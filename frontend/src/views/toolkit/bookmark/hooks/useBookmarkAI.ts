import { ref, h, defineComponent, reactive } from 'vue'
import { useMessage, useDialog, NDynamicTags, NAlert, NButton, NSpace } from 'naive-ui'
import axios from 'axios'

// 辅助函数：获取认证头
const getAuthHeaders = () => {
  const token = localStorage.getItem('lens_access_token')
  return token ? { 'Authorization': `Bearer ${token}` } : {}
}

// 辅助函数：带认证的fetch
const authFetch = async (url: string, options: RequestInit = {}) => {
  return fetch(url, {
    ...options,
    headers: {
      ...options.headers,
      ...getAuthHeaders()
    }
  })
}

const DEFAULT_CATEGORIES = [
  "AI智能工具", "编程与开发", "设计与素材", "办公与协作",
  "网络与安全", "服务器与 NAS", "在线工具箱", "软件与资源",
  "影视与流媒体", "动漫与二次元", "游戏与电竞", "音乐与音频",
  "资讯与阅读", "社区与论坛", "知识与百科", "生活与消费",
  "金融与资产", "未分类/其他"
]

const AIConfigEditor = defineComponent({
  props: ['targetFolderName', 'data'],
  setup(props) {
    const handleRestore = () => {
      props.data.categories = [...DEFAULT_CATEGORIES]
    }

    return () => h('div', { style: 'display: flex; flex-direction: column; gap: 16px;' }, [
      h(NAlert, { title: '范围确认', type: 'warning', bordered: false }, {
        default: () => [
          h('div', null, `整理目标：${props.targetFolderName}`),
          h('div', { style: 'font-size: 12px; margin-top: 4px; opacity: 0.7;' }, '💡 提示：你可以通过左侧目录树选中特定文件夹进行局部处理。')
        ]
      }),
      h('div', null, [
        h('div', { style: 'display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px;' }, [
          h('span', { style: 'font-weight: bold;' }, '分类标准预设：'),
          h(NButton, { size: 'tiny', quaternary: true, type: 'primary', onClick: handleRestore }, { default: () => '恢复系统默认' })
        ]),
        h(NDynamicTags, {
          value: props.data.categories,
          'onUpdate:value': (val: string[]) => { props.data.categories = val }
        }),
        h('p', { style: 'color: #999; font-size: 12px; margin-top: 10px;' }, 'AI 将严格按此列表归类（严禁自建）。请手动剔除不想要的分类。')
      ])
    ])
  }
})

export function useBookmarkAI(bookmarkApi: any, actions: any, state: any) {
  const message = useMessage()
  const dialog = useDialog()
  const isOrganizing = ref(false)

  const handleAIAnalyze = async () => {
    if (isOrganizing.value) return
    
    const dialogData = reactive({
      categories: [] as string[]
    })

    // 加载数据
    try {
      const res = await axios.get('/api/system/config')
      let raw = res.data.ai_bookmark_categories
      
      // 深度解析：处理后端可能返回的 JSON 字符串
      if (typeof raw === 'string') {
        try { raw = JSON.parse(raw) } catch (e) {}
      }
      
      dialogData.categories = (Array.isArray(raw) && raw.length > 0) ? raw : [...DEFAULT_CATEGORIES]
    } catch (e) {
      dialogData.categories = [...DEFAULT_CATEGORIES]
    }

    const selectedFolderId = state.selectedKeys.value[0]
    const targetFolderId = (selectedFolderId === 'root' || !selectedFolderId) ? null : selectedFolderId
    const targetFolderName = targetFolderId ? actions.findItemById(state.bookmarks.value, targetFolderId)?.title : '全部书签'

    const d = dialog.info({
      title: 'AI 整理配置',
      style: 'width: 520px',
      content: () => h(AIConfigEditor, {
        targetFolderName,
        data: dialogData
      }),
      action: () => h(NSpace, { justify: 'end' }, {
        default: () => [
          h(NButton, { 
            quaternary: true,
            onClick: () => { d.destroy() } 
          }, { default: () => '取消' }),
          h(NButton, { 
            secondary: true, 
            type: 'info',
            onClick: async () => {
              await saveCategories(dialogData.categories)
              message.success('预设已保存')
              d.destroy()
            }
          }, { default: () => '仅保存分类' }),
          h(NButton, { 
            type: 'primary',
            onClick: async () => {
              await saveCategories(dialogData.categories)
              d.destroy()
              startOrganize(targetFolderId, targetFolderName)
            }
          }, { default: () => '启动 AI 整理' })
        ]
      })
    })
  }

  const saveCategories = async (cats: string[]) => {
    return axios.post('/api/system/config', {
      configs: [{ key: 'ai_bookmark_categories', value: cats }]
    })
  }

  const startOrganize = async (targetFolderId: string | null, targetFolderName: string) => {
    isOrganizing.value = true
    message.info(`AI 整理任务已启动 [${targetFolderName}]`, { duration: 5000 })
    
    try {
      const response = await authFetch('/api/bookmarks/ai-auto-organize', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ folder_id: targetFolderId })
      })

      if (!response.ok) throw new Error('网络请求失败')
      const reader = response.body?.getReader()
      if (!reader) return

      const decoder = new TextDecoder()
      console.log(`--- 🤖 AI 书签整理 [${targetFolderName}] 开始 ---`)

      while (true) {
        const { done, value } = await reader.read()
        if (done) break
        const chunk = decoder.decode(value)
        chunk.split('\n').forEach(line => {
          if (line.startsWith('data: ')) {
            console.log(`[AI] ${line.replace('data: ', '').trim()}`)
          }
        })
      }

      console.log('--- ✅ AI 书签整理全部完成 ---')
      message.success('AI 整理已全部完成！')
      await actions.refreshCurrentFolder()
    } catch (err: any) {
      console.error('[AI Error]', err)
      message.error('AI 整理任务异常: ' + err.message)
    } finally {
      isOrganizing.value = false
    }
  }

  return {
    handleAIAnalyze,
    isOrganizing
  }
}