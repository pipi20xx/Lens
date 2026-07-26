import { api } from './client'

export const systemApi = {
  // ========== 系统配置 ==========
  getConfig: () => api.get('/api/system/config'),
  saveConfig: (configs: any[]) => api.post('/api/system/config', { configs }),
  exportConfig: () => api.get('/api/system/config/export'),
  importConfig: (formData: FormData) => api.post('/api/system/config/import', formData),
  generateToken: () => api.post('/api/system/token/generate'),

  // ========== 版本 & 升级 ==========
  getVersion: () => api.get('/api/system/version'),
  upgrade: (hostId?: string) =>
    api.post('/api/system/upgrade', null, { params: { host_id: hostId } }),
  upgradeSystem: (hostId?: string) =>
    api.post('/api/system/upgrade', null, { params: { host_id: hostId } }),

  // ========== 审计日志 ==========
  getAuditLogs: (params?: { page?: number; page_size?: number }) =>
    api.get('/api/system/audit/logs', { params }),

  // ========== 系统日志 ==========
  getLogDates: () => api.get('/api/system/logs/dates'),
  getLogContent: (date: string) => api.get(`/api/system/logs/content/${date}`),
  getRawLog: (type?: string) =>
    api.get('/api/system/logs/raw', { params: { type } }),
  exportLog: (date: string) => api.get(`/api/system/logs/export/${date}`),

  // ========== 系统状态 ==========
  getStatus: () => api.get('/api/status'),
  getStats: () => api.get('/api/stats/summary'),

  // ========== API 文档 ==========
  getDocsUrl: (token?: string) =>
    `/api/system/docs${token ? `?token=${token}` : ''}`,
}
