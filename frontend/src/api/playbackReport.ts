import { api } from './client'

export const playbackReportApi = {
  // 概览
  getSummary: (days?: number) =>
    api.get('/api/playback-report/summary', { params: { days } }),

  // 播放活跃度流水
  getActivity: (days?: number) =>
    api.get('/api/playback-report/activity', { params: { days } }),

  // 用户统计名单
  getUsers: () => api.get('/api/playback-report/users'),

  // 特定用户信息
  getUserInfo: (userId: string) =>
    api.get(`/api/playback-report/users/${userId}`),

  // 播放活跃度图表
  getPlayActivity: (itemType?: string, days?: number) =>
    api.get('/api/playback-report/play-activity', {
      params: { item_type: itemType, days },
    }),

  // 特定报表
  getReport: (reportType: string, days?: number, userId?: string) => {
    const formattedType = reportType.replace(/\//g, '-')
    return api.get(`/api/playback-report/reports/${formattedType}`, {
      params: { days, user_id: userId },
    })
  },

  // 报表项
  getReportItems: (parentId?: string) =>
    api.get('/api/playback-report/report-items', { params: { parent_id: parentId } }),

  // 会话列表
  getSessions: () => api.get('/api/playback-report/sessions'),

  // 播放清单统计
  getPlaylist: (days?: number) =>
    api.get('/api/playback-report/playlist', { params: { days } }),

  // 媒体库统计概览 (4K, HDR等)
  getLibrarySummary: () => api.get('/api/playback-report/library-summary'),

  // 配置
  getConfig: () => api.get('/api/playback-report/config'),
  updateConfig: (config: any) => api.post('/api/playback-report/config', config),

  // 自定义 SQL 查询
  customQuery: (query: string) =>
    api.post('/api/playback-report/query', { query }),

  // 图片代理
  imageProxyUrl: (itemId?: string, name?: string, type?: string) => {
    const params = new URLSearchParams()
    if (itemId) params.set('item_id', itemId)
    if (name) params.set('name', name)
    if (type) params.set('type', type)
    return `/api/playback-report/image-proxy?${params.toString()}`
  },
}
