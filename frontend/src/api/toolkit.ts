import { api } from './client'

export const toolkitApi = {
  // 通用执行方法 (兼容旧前端 toolkitApi.executeAction)
  executeAction: (endpoint: string, data: any) => api.post(`/api/toolkit/${endpoint}`, data),

  // ========== 类型映射器 ==========
  mapper: (data: any) => api.post('/api/toolkit/mapper', data),
  genreAdder: (data: any) => api.post('/api/toolkit/genre_adder', data),
  genreRemover: (data: any) => api.post('/api/toolkit/remover', data),
  peopleRemover: (data: any) => api.post('/api/toolkit/people_remover', data),
  metadataFieldUnlocker: (data: any) => api.post('/api/toolkit/metadata_field_unlocker', data),
  itemLocker: (data: any) => api.post('/api/toolkit/item_locker', data),
  itemUnlocker: (data: any) => api.post('/api/toolkit/item_unlocker', data),
  episodeDeleter: (data: any) => api.post('/api/toolkit/episode_deleter', data),

  // ========== HD-Icons ==========
  getHdIcons: () => api.get('/api/toolkit/navigation/hd-icons'),

  // ========== 去重 (后端路由: /api/dedupe) ==========
  dedupe: {
    getSyncStatus: () => api.get('/api/dedupe/sync/status'),
    syncMedia: () => api.post('/api/dedupe/sync'),
    scan: () => api.post('/api/dedupe/sync'),
    getItems: (params?: any) => api.get('/api/dedupe/items', { params }),
    getDuplicates: () => api.get('/api/dedupe/duplicates'),
    smartSelect: () => api.post('/api/dedupe/smart-select'),
    deleteItems: (itemIds: string[]) => api.delete('/api/dedupe/items', { data: { item_ids: itemIds } }),
    getConfig: () => api.get('/api/dedupe/config'),
    saveConfig: (data: any) => api.post('/api/dedupe/config', data),
  },

  // ========== 自动标签 (后端路由: /api/autotags) ==========
  autotags: {
    getRules: () => api.get('/api/autotags/rules'),
    saveRules: (rules: any[]) => api.post('/api/autotags/rules', rules),
    testWrite: (itemId: string, tag: string) => api.post('/api/autotags/test-write', { item_id: itemId, tag }),
    execute: (data: any) => api.post('/api/autotags/execute', data),
    clearAll: () => api.post('/api/autotags/clear-all'),
    clearSpecific: (data: any) => api.post('/api/autotags/clear-specific', { tags: data }),
    getWebhookConfig: () => api.get('/api/autotags/webhook-config'),
    saveWebhookConfig: (data: any) => api.post('/api/autotags/webhook-config', data),
  },

  // ========== AI 实验室 (后端路由: /api/ai) ==========
  aiLab: {
    getConfig: () => api.get('/api/ai/config'),
    saveConfig: (data: any) => api.post('/api/ai/config', data),
    chat: (messages: any[]) => api.post('/api/ai/chat', { messages }),
    search: (keyword: string) => api.get('/api/ai/search', { params: { keyword } }),
    match: (itemId: string) => api.post(`/api/ai/match/${itemId}`),
    fix: (itemId: string) => api.post(`/api/ai/fix/${itemId}`),
  },

  // ========== 演员实验室 (后端路由: /api/actor-lab) ==========
  actorLab: {
    analyze: (params: any) => api.get('/api/actor-lab/analyze', { params }),
    search: (keyword: string) => api.get('/api/actor-lab/analyze', { params: { query: keyword } }),
    scanPhotos: (actorId: string) => api.post(`/api/actor-lab/${actorId}/scan-photos`),
    updateInfo: (actorId: string) => api.post(`/api/actor-lab/${actorId}/update-info`),
  },

  // ========== Emby 条目查询 (后端路由: /api/items) ==========
  embyItemQuery: {
    search: (keyword: string, type?: string) => api.get('/api/items/query', { params: { keyword, type } }),
    getDetail: (itemId: string) => api.get('/api/items/info', { params: { item_id: itemId } }),
    fixMatch: (itemId: string) => api.post(`/api/items/${itemId}/fix-match`),
  },

  // ========== TMDB (后端路由: /api/tmdb, /api/tmdb-lab, /api/tmdb-search) ==========
  tmdb: {
    // TMDB 实验室
    search: (params: any) => api.get('/api/tmdb-lab/search', { params }),
    fetch: (params: any) => api.get('/api/tmdb-lab/fetch', { params }),
    fetchSeason: (params: any) => api.get('/api/tmdb-lab/fetch-season', { params }),
    fetchEpisode: (params: any) => api.get('/api/tmdb-lab/fetch-episode', { params }),
    getDetail: (id: number, type: string) => api.get(`/api/tmdb-lab/${type}/${id}`),
    // TMDB 反向查找
    reverseLookup: (episodeId: string) => api.get('/api/tmdb/reverse-tmdb', { params: { episode_id: episodeId } }),
    searchById: (data: any) => api.post('/api/tmdb-search/search-by-id', data),
    applyMatch: (embyId: string, tmdbId: string) => api.post('/api/tmdb/apply-match', { emby_id: embyId, tmdb_id: tmdbId }),
    linkToEmby: (tmdbId: number, embyId: string) => api.post('/api/tmdb/link-to-emby', { tmdb_id: tmdbId, emby_id: embyId }),
    fixMatch: (itemId: string) => api.post(`/api/tmdb/fix-match/${itemId}`),
  },

  // ========== 清理工具 ==========
  cleanup: {
    scanEmptySeries: () => api.get('/api/toolkit/cleanup/empty-series'),
    scanEmptyFolders: () => api.get('/api/toolkit/cleanup/empty-folders'),
    deleteEmptySeries: (ids: string[]) => api.post('/api/toolkit/cleanup/delete-empty-series', { ids }),
    cleanUnusedMedia: () => api.post('/api/toolkit/cleanup/clean-unused-media'),
  },

  // ========== 锁定管理 ==========
  lockManager: {
    getLocks: () => api.get('/api/toolkit/locks'),
    unlock: (id: string) => api.post(`/api/toolkit/locks/${id}/unlock`),
    unlockAll: () => api.post('/api/toolkit/locks/unlock-all'),
  },

  // ========== 类型管理 ==========
  typeManager: {
    getTypes: () => api.get('/api/toolkit/navigation/hd-icons'),
    renameType: (id: string, newName: string) => api.put(`/api/toolkit/type-manager/types/${id}`, { name: newName }),
    deleteType: (id: string) => api.delete(`/api/toolkit/type-manager/types/${id}`),
  },
}
