import { api } from './client'

/**
 * 旧版 accountApi 已迁移至 /api/emby-users/*
 * 后端 server router 不再提供 /users /users/sync 等路由
 * 此文件保留兼容性，实际调用 emby-users 接口
 */
export const accountApi = {
  getUsers: (serverId?: string) => api.get('/api/emby-users/list', { params: { server_id: serverId } }),
  createUser: (name: string, serverId?: string) => api.post('/api/emby-users/create', null, { params: { name, server_id: serverId } }),
  deleteUser: (userId: string, serverId?: string) => api.delete(`/api/emby-users/${userId}`, { params: { server_id: serverId } }),
  getUserInfo: (userId: string, serverId?: string) => api.get(`/api/emby-users/${userId}/info`, { params: { server_id: serverId } }),
  updateUserPolicy: (userId: string, policy: any, serverId?: string) => api.post(`/api/emby-users/${userId}/policy`, policy, { params: { server_id: serverId } }),
  updatePassword: (userId: string, password: string, serverId?: string) => api.post(`/api/emby-users/${userId}/password`, { password }, { params: { server_id: serverId } }),
}
