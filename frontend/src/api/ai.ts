import { api } from './client'

export const aiApi = {
  getConfig: () => api.get('/api/ai/config'),
  updateConfig: (data: any) => api.post('/api/ai/config', data),
  chat: (messages: any[]) => api.post('/api/ai/chat', { messages }),
  getModels: () => api.get('/api/ai/models'),
}
