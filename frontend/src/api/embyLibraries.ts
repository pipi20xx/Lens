import { api } from './client'

export const embyLibrariesApi = {
  list: (serverId?: string) =>
    api.get('/api/emby-libraries/list', { params: { server_id: serverId } }),

  add: (name: string, collectionType: string, path?: string, serverId?: string) =>
    api.post('/api/emby-libraries/add', null, {
      params: { name, collection_type: collectionType, path, server_id: serverId },
    }),

  update: (libraryData: any, serverId?: string) =>
    api.post('/api/emby-libraries/update', libraryData, { params: { server_id: serverId } }),

  remove: (name: string, id: string, serverId?: string) =>
    api.delete('/api/emby-libraries/remove', {
      params: { name, id, server_id: serverId },
    }),
}
