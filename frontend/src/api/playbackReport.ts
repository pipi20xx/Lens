import { api } from './client'

export const playbackReportApi = {
  getReports: (params?: any) => api.get('/api/playback-report', { params }),
  getStats: (params?: any) => api.get('/api/playback-report/stats', { params }),
  exportReport: (params?: any) => api.get('/api/playback-report/export', { params }),
}
