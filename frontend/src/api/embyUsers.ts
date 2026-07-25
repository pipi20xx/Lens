import { api } from './client'

export const embyUsersApi = {
  getUsers: () => api.get('/api/emby/users'),
  getUser: (id: string) => api.get(`/api/emby/users/${id}`),
  deleteUser: (id: string) => api.delete(`/api/emby/users/${id}`),
  updateUser: (id: string, data: any) => api.put(`/api/emby/users/${id}`, data),
  updateUserPolicy: (id: string, policy: any) => api.post(`/api/emby/users/${id}/policy`, policy),
  resetPassword: (id: string) => api.post(`/api/emby/users/${id}/reset-password`),
}
