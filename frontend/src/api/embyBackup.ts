import { api } from './client'

export const embyBackupApi = {
  list: (category: 'users' | 'libraries', serverId?: string) =>
    api.get('/api/emby-backup/list', { params: { category, server_id: serverId } }),

  create: (category: 'users' | 'libraries', id: string, name: string, serverId?: string) =>
    api.post('/api/emby-backup/create', null, { params: { category, id, name, server_id: serverId } }),

  createAll: (category: 'users' | 'libraries', serverId?: string) =>
    api.post('/api/emby-backup/create-all', null, { params: { category, server_id: serverId } }),

  restore: (category: 'users' | 'libraries', filename: string, serverId?: string) =>
    api.post('/api/emby-backup/restore', null, { params: { category, filename, server_id: serverId } }),

  restoreAll: (category: 'users' | 'libraries', serverId?: string) =>
    api.post('/api/emby-backup/restore-all', null, { params: { category, server_id: serverId } }),

  delete: (category: 'users' | 'libraries', filename: string) =>
    api.delete('/api/emby-backup/delete', { params: { category, filename } }),

  clear: (category: 'users' | 'libraries') =>
    api.delete('/api/emby-backup/clear', { params: { category } }),
}
