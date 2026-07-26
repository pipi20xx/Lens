import { api } from './client'

export function listEmbyUsers(serverId?: string) {
  return api.get('/api/emby-users/list', { params: { server_id: serverId } })
}

export function createEmbyUser(name: string, serverId?: string) {
  return api.post('/api/emby-users/create', null, { params: { name, server_id: serverId } })
}

export function deleteEmbyUser(userId: string, serverId?: string) {
  return api.delete(`/api/emby-users/${userId}`, { params: { server_id: serverId } })
}

export function getEmbyUserInfo(userId: string, serverId?: string) {
  return api.get(`/api/emby-users/${userId}/info`, { params: { server_id: serverId } })
}

export function updateEmbyUserPolicy(userId: string, policy: any, serverId?: string) {
  return api.post(`/api/emby-users/${userId}/policy`, policy, { params: { server_id: serverId } })
}

export function updateEmbyUserPassword(userId: string, password: string, serverId?: string) {
  return api.post(`/api/emby-users/${userId}/password`, { password }, { params: { server_id: serverId } })
}

// 兼容旧版对象式调用
export const embyUsersApi = {
  list: listEmbyUsers,
  getUsers: listEmbyUsers,
  create: createEmbyUser,
  createUser: createEmbyUser,
  deleteUser: deleteEmbyUser,
  getInfo: getEmbyUserInfo,
  updatePolicy: updateEmbyUserPolicy,
  updateUserPolicy: updateEmbyUserPolicy,
  updatePassword: (userId: string, data: any, serverId?: string) =>
    api.post(`/api/emby-users/${userId}/password`, data, { params: { server_id: serverId } }),
}
