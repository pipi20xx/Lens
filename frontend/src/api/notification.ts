import { api } from './client'

export const notificationApi = {
  getSettings: () => api.get('/api/notification/settings'),
  saveSettings: (data: any) => api.post('/api/notification/settings', data),
  addBot: (data: any) => api.post('/api/notification/bots', data),
  updateBot: (id: string, data: any) => api.put(`/api/notification/bots/${id}`, data),
  deleteBot: (id: string) => api.delete(`/api/notification/bots/${id}`),
  testBot: (data: { bot_id: string; message: string }) =>
    api.post('/api/notification/test', data),
}
