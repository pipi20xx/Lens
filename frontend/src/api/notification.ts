import { api } from './client'

export const notificationApi = {
  getChannels: () => api.get('/api/notification/channels'),
  createChannel: (data: any) => api.post('/api/notification/channels', data),
  updateChannel: (id: string, data: any) => api.put(`/api/notification/channels/${id}`, data),
  deleteChannel: (id: string) => api.delete(`/api/notification/channels/${id}`),
  testChannel: (id: string) => api.post(`/api/notification/channels/${id}/test`),
}
