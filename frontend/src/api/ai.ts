import { api } from './client'

export const aiApi = {
  getConfig: () => api.get('/api/ai/config'),
  saveConfig: (data: { provider: string; api_key: string; base_url: string; model: string }) =>
    api.post('/api/ai/config', data),
  chat: (messages: any[]) => api.post('/api/ai/chat', { messages }),
}
