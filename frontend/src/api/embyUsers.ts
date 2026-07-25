import { api } from './client'

export const embyUsersApi = {
  list: (serverId?: string) =>
    api.get('/api/emby-users/list', { params: { server_id: serverId } }),

  create: (name: string, serverId?: string) =>
    api.post('/api/emby-users/create', null, { params: { name, server_id: serverId } }),

  delete: (userId: string, serverId?: string) =>
    api.delete(`/api/emby-users/${userId}`, { params: { server_id: serverId } }),

  getInfo: (userId: string, serverId?: string) =>
    api.get(`/api/emby-users/${userId}/info`, { params: { server_id: serverId } }),

  updatePolicy: (userId: string, policy: any, serverId?: string) =>
    api.post(`/api/emby-users/${userId}/policy`, policy, { params: { server_id: serverId } }),

  updatePassword: (userId: string, password: string, serverId?: string) =>
    api.post(`/api/emby-users/${userId}/password`, { password }, { params: { server_id: serverId } }),
}
