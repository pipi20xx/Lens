import { api } from './client'
import type { LoginParams, LoginResponse } from '@/types'

export const authApi = {
  login: (data: LoginParams) => api.post<LoginResponse>('/api/auth/login', data),
  getMe: () => api.get('/api/auth/me'),
  changePassword: (data: { old_password: string; new_password: string }) => api.post('/api/auth/password', data),
  get2faSetup: () => api.get('/api/auth/2fa/setup'),
  enable2fa: (code: string) => api.post(`/api/auth/2fa/enable?code=${code}`),
  disable2fa: () => api.post('/api/auth/2fa/disable'),
  getSessions: () => api.get('/api/auth/sessions'),
  revokeSession: (id: string) => api.delete(`/api/auth/sessions/${id}`),
  revokeAllSessions: () => api.delete('/api/auth/sessions'),
  // 系统配置（旧版 authApi 里混了，这里保留兼容）
  updateSystemConfig: (configs: any[]) => api.post('/api/system/config', { configs }),
  getSessionConfig: () => api.get('/api/server/current'),
}
