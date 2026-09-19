import { api } from './client'

export const notificationApi = {
  getSettings: () => api.get('/api/notification/settings'),
  saveSettings: (data: any) => api.post('/api/notification/settings', data),
  addBot: (data: any) => api.post('/api/notification/bots', data),
  updateBot: (id: string, data: any) => api.put(`/api/notification/bots/${id}`, data),
  deleteBot: (id: string) => api.delete(`/api/notification/bots/${id}`),
  testBot: (data: { bot_id: string; message: string }) =>
    api.post('/api/notification/test', data),
  /** Bot 运行时状态（在线徽章） */
  getBotStatus: (id: string) => api.get(`/api/notification/bots/${id}/status`),
  /** 校验 Bot Token 有效性（getMe），返回 { valid, username, error } */
  validateBot: (token: string) =>
    api.post<{ valid: boolean; username: string | null; error: string | null }>(
      '/api/notification/bots/validate',
      { token }
    ),
}
