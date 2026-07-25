import { api } from './client'

export const accountApi = {
  // 个人账户
  getProfile: () => api.get('/api/auth/me'),
  changePassword: (data: { old_password: string; new_password: string }) => api.post('/api/auth/password', data),
  getSessions: () => api.get('/api/auth/sessions'),
  revokeSession: (id: string) => api.delete(`/api/auth/sessions/${id}`),
  revokeAllSessions: () => api.delete('/api/auth/sessions'),
  setup2fa: () => api.get('/api/auth/2fa/setup'),
  enable2fa: (code: string) => api.post(`/api/auth/2fa/enable?code=${code}`),
  disable2fa: () => api.post('/api/auth/2fa/disable'),
}
