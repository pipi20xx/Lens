import { api } from './client'

export const configApi = {
  getConfig: (key: string) => api.get('/api/system/config', { params: { key } }),
  updateConfig: (configs: any[]) => api.post('/api/system/config', { configs }),
}
