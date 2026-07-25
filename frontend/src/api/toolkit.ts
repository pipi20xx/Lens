import { api } from './client'

export const toolkitApi = {
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

  // ========== 去重 ==========
  dedupe: {
    getSyncStatus: () => api.get('/api/dedupe/sync/status'),
    syncMedia: () => api.post('/api/dedupe/sync'),
    getItems: (params?: any) => api.get('/api/dedupe/items', { params }),
    getDuplicates: () => api.get('/api/dedupe/duplicates'),
    smartSelect: () => api.post('/api/dedupe/smart-select'),
    deleteItems: (itemIds: string[]) => api.delete('/api/dedupe/items', { item_ids: itemIds }),
    getConfig: () => api.get('/api/dedupe/config'),
    saveConfig: (data: any) => api.post('/api/dedupe/config', data),
  },

  // ========== 自动标签 ==========
  autotags: {
    getRules: () => api.get('/api/autotags/rules'),
    createRule: (data: any) => api.post('/api/autotags/rules', data),
    updateRule: (id: string, data: any) => api.put(`/api/autotags/rules/${id}`, data),
    deleteRule: (id: string) => api.delete(`/api/autotags/rules/${id}`),
    testWrite: (data: any) => api.post('/api/autotags/test-write', data),
    execute: (data: any) => api.post('/api/autotags/execute', data),
    clearAll: () => api.post('/api/autotags/clear-all'),
    clearSpecific: (data: any) => api.post('/api/autotags/clear-specific', data),
    getWebhookConfig: () => api.get('/api/autotags/webhook-config'),
    saveWebhookConfig: (data: any) => api.post('/api/autotags/webhook-config', data),
  },

  // ========== 外部控制 ==========
  externalControl: {
    getConfig: () => api.get('/api/toolkit/external-control/config'),
    updateConfig: (data: any) => api.post('/api/toolkit/external-control/config', data),
  },

  // ========== 演员实验室 ==========
  actorLab: {
    analyze: (params: any) => api.get('/api/actor-lab/analyze', { params }),
  },
}
