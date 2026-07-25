import { api } from './client'

export const webhookApi = {
  getLogs: () => api.get('/api/webhook/list'),
  clearLogs: () => api.delete('/api/webhook/clear'),
}
