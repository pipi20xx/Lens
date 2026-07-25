import { api } from './client'
import type { LoginParams, LoginResponse } from '@/types'

export const authApi = {
  login: (data: LoginParams) => api.post<LoginResponse>('/api/auth/login', data),
  changePassword: (data: { old_password: string; new_password: string }) => api.post('/api/auth/change-password', data),
  get2faSetup: () => api.get<{ secret: string; qr_code: string }>('/api/auth/2fa/setup'),
  enable2fa: (code: string) => api.post('/api/auth/2fa/enable', { code }),
  disable2fa: (code: string) => api.post('/api/auth/2fa/disable', { code }),
}
