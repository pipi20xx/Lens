import { api } from './client'

export const serverApi = {
  // ========== 服务器管理 (后端路由: /api/server/*) ==========
  getServers: () => api.get('/api/server/list'),
  getCurrent: () => api.get('/api/server/current'),
  saveGlobal: (data: any) => api.post('/api/server/save', data),
  activateServer: (id: string) => api.post(`/api/server/activate/${id}`),
  deleteServer: (id: string) => api.delete(`/api/server/${id}`),
  testConnection: (config: { url: string; api_key: string }) =>
    api.post('/api/server/test', config),

  // ========== Emby 媒体库 (后端路由: /api/server/libraries) ==========
  getLibraries: () => api.get('/api/server/libraries'),

  // ========== Emby 用户 (后端路由: /api/emby-users/*) ==========
  // 注意: /api/server/users 和 /api/server/users/sync 已废弃
  // 统一使用 /api/emby-users/list
  getUsers: (serverId?: string) => api.get('/api/emby-users/list', { params: { server_id: serverId } }),

  // ========== 批量获取 Emby 项目 (后端路由: /api/server/items) ==========
  getItems: (ids: string, fields?: string) =>
    api.get('/api/server/items', { params: { ids, fields } }),
}
