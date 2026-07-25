import { api } from './client'

export const accountApi = {
  getProfile: () => api.get('/api/auth/profile'),
  updateProfile: (data: any) => api.put('/api/auth/profile', data),
  changePassword: (data: { old_password: string; new_password: string }) => api.post('/api/auth/change-password', data),
}
