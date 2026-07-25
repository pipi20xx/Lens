import { api } from './client'

export const systemApi = {
  getConfig: () => api.get('/api/system/config'),
  updateConfig: (configs: any[]) => api.post('/api/system/config', { configs }),
  getVersion: () => api.get('/api/system/version'),
  getStats: () => api.get('/api/stats'),
  getDocs: () => api.get('/api/system/docs'),
}
