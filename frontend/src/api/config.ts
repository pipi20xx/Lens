import { api } from './client'

export const configApi = {
  getConfig: () => api.get('/api/system/config'),
  updateConfig: (configs: any[]) => api.post('/api/system/config', { configs }),
  exportConfig: () => api.get('/api/system/config/export'),
  importConfig: (formData: FormData) => api.post('/api/system/config/import', formData),
  generateToken: () => api.post('/api/system/token/generate'),
}
