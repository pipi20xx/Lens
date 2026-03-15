import { ref, reactive } from 'vue'
import { useMessage } from 'naive-ui'
import { systemApi } from '@/api/system'
import { copyText } from '@/utils/clipboard'

export function useExternalControl() {
  const message = useMessage()
  const loadingLogs = ref(false)
  const auditLogs = ref([])
  const showLogDetail = ref(false)
  const currentPayload = ref('')
  const activeTab = ref('api_key')
  const showFullToken = ref(false)

  const pagination = reactive({
    page: 1,
    pageSize: 15,
    itemCount: 0,
    showSizePicker: true,
    pageSizes: [15, 30, 50],
  })

  const config = reactive({ api_token: '', audit_enabled: true })

  const loadConfig = async () => {
    try {
      const data: any = await systemApi.getConfig()
      config.api_token = data.api_token || ''
      config.audit_enabled = data.audit_enabled !== 'false' && data.audit_enabled !== false
    } catch (err) { /* 拦截器已处理弹窗 */ }
  }

  const saveSettings = async () => {
    try {
      await systemApi.saveConfig([
        { key: 'audit_enabled', value: String(config.audit_enabled) }
      ])
      message.success('设置已保存')
    } catch (err) { }
  }

  const generateNewToken = async () => {
    try {
      const data: any = await systemApi.generateToken()
      const newToken = data.token
      await systemApi.saveConfig([{ key: 'api_token', value: newToken }])
      config.api_token = newToken
      message.success('新 Token 已生成')
    } catch (err) { }
  }

  const copyToken = async () => {
    if (await copyText(config.api_token)) {
      message.info('Token 已复制到剪贴板')
    } else {
      message.error('复制失败，请手动复制')
    }
  }

  const fetchLogs = async () => {
    loadingLogs.value = true
    try {
      const data: any = await systemApi.getAuditLogs({ page: pagination.page, page_size: pagination.pageSize })
      // 注意这里：data 已经是后端返回的对象了，不需要 .data
      auditLogs.value = data.items || []
      pagination.itemCount = data.total || 0
    } catch (err) { }
    finally { loadingLogs.value = false }
  }

  const handlePageChange = (page: number) => { pagination.page = page; fetchLogs() }
  const handlePageSizeChange = (pageSize: number) => { pagination.pageSize = pageSize; pagination.page = 1; fetchLogs() }

  return {
    config, auditLogs, loadingLogs, pagination, showLogDetail, currentPayload, activeTab, showFullToken,
    loadConfig, saveSettings, generateNewToken, copyToken, fetchLogs, handlePageChange, handlePageSizeChange
  }
}