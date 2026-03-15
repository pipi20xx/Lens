import request from '@/utils/request'

export const authApi = {
  getMe: () => request.get('/api/auth/me'),
  setup2fa: () => request.get('/api/auth/2fa/setup'),
  enable2fa: (code: string) => request.post(`/api/auth/2fa/enable?code=${code}`),
  disable2fa: () => request.post('/api/auth/2fa/disable'),
  updateSystemConfig: (configs: any[]) => request.post('/api/system/config', { configs }),
  changePassword: (data: any) => request.post('/api/auth/password', data)
}