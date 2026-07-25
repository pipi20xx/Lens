import { api } from './client'

export const serverApi = {
  // 服务器列表
  getServers: () => api.get('/api/server/list'),
  getCurrent: () => api.get('/api/server/current'),
  saveGlobal: (data: any) => api.post('/api/server/save', data),
  activateServer: (id: string) => api.post(`/api/server/activate/${id}`),
  deleteServer: (id: string) => api.delete(`/api/server/${id}`),

  // 测试连接
  testConnection: (config: { url: string; api_key: string }) =>
    api.post('/api/server/test', config),

  // Emby 登录
  embyLogin: (serverId?: string) =>
    api.post('/api/server/login', { server_id: serverId }),

  // 媒体库 & 用户 (从 Server 路由提供)
  getLibraries: () => api.get('/api/server/libraries'),
  getUsers: () => api.get('/api/server/users'),
  syncUsers: () => api.post('/api/server/users/sync'),

  // 批量获取 Emby 项目
  getItems: (ids: string, fields?: string) =>
    api.get('/api/server/items', { params: { ids, fields } }),
}
