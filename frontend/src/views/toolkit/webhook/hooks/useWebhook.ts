import { ref, h } from 'vue'
import { useMessage, useDialog, NButton, NIcon, NSpace } from 'naive-ui'
import {
  TrashIcon,
  XMarkIcon
} from '@heroicons/vue/24/outline'
import { webhookApi } from '@/api/webhook'

export function useWebhook() {
  const message = useMessage()
  const dialog = useDialog()
  const loading = ref(false)
  const logs = ref([])
  const showModal = ref(false)
  const selectedPayload = ref({})

  const renderIcon = (icon: any) => {
    return () => h(NIcon, null, { default: () => h(icon) })
  }

  const fetchLogs = async () => {
    loading.value = true
    try {
      const res: any = await webhookApi.getLogs()
      logs.value = res
    } catch (e) {
      message.error('加载日志失败')
    } finally {
      loading.value = false
    }
  }

  const handleClear = () => {
    const d = dialog.warning({
      title: '确认清空日志',
      content: '确定要物理删除所有的 Webhook 历史记录吗？此操作无法撤销。',
      action: () => h(NSpace, { justify: 'end' }, {
        default: () => [
          h(NButton, { 
            size: 'small', 
            onClick: () => d.destroy() 
          }, { 
            icon: renderIcon(XMarkIcon),
            default: () => '取消' 
          }),
          h(NButton, { 
            size: 'small', 
            type: 'error', 
            secondary: true,
            onClick: async () => {
              d.loading = true
              try {
                await webhookApi.clearLogs()
                message.success('日志已全部物理清理')
                d.destroy()
                fetchLogs()
              } catch (e) {
                message.error('清理失败')
              } finally {
                d.loading = false
              }
            }
          }, { 
            icon: renderIcon(TrashIcon),
            default: () => '确定清空' 
          })
        ]
      })
    })
  }

  const showJson = (payload: any) => {
    selectedPayload.value = payload
    showModal.value = true
  }

  return {
    loading, logs, showModal, selectedPayload,
    fetchLogs, handleClear, showJson
  }
}