import { api } from './client'

export function listEmbyLibraries(serverId?: string) {
  return api.get('/api/emby-libraries/list', { params: { server_id: serverId } })
}

export function addEmbyLibrary(name: string, collectionType: string, path?: string, serverId?: string) {
  return api.post('/api/emby-libraries/add', null, {
    params: { name, collection_type: collectionType, path, server_id: serverId },
  })
}

export function updateEmbyLibrary(libraryData: any, serverId?: string) {
  return api.post('/api/emby-libraries/update', libraryData, { params: { server_id: serverId } })
}

export function removeEmbyLibrary(name: string, id: string, serverId?: string) {
  return api.delete('/api/emby-libraries/remove', {
    params: { name, id, server_id: serverId },
  })
}

// 兼容旧版对象式调用
export const embyLibrariesApi = {
  list: listEmbyLibraries,
  getLibraries: listEmbyLibraries,
  add: addEmbyLibrary,
  update: updateEmbyLibrary,
  remove: removeEmbyLibrary,
  refreshLibrary: (itemId: string, serverId?: string) =>
    api.post('/api/emby-libraries/update', { ItemId: itemId }, { params: { server_id: serverId } }),
  backupAll: (serverId?: string) =>
    api.post('/api/emby-libraries/backup', null, { params: { server_id: serverId } }),
}
