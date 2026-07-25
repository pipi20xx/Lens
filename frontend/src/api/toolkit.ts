import { api } from './client'

export const toolkitApi = {
  dedupe: {
    scan: (params?: any) => api.post('/api/dedupe/scan', params),
    getResults: () => api.get('/api/dedupe/results'),
    deleteItems: (ids: string[]) => api.post('/api/dedupe/delete', { ids }),
  },
  autotags: {
    getRules: () => api.get('/api/autotags/rules'),
    createRule: (data: any) => api.post('/api/autotags/rules', data),
    updateRule: (id: string, data: any) => api.put(`/api/autotags/rules/${id}`, data),
    deleteRule: (id: string) => api.delete(`/api/autotags/rules/${id}`),
  },
  navigation: {
    getNavItems: () => api.get('/api/navigation/items'),
    updateNavItems: (items: any[]) => api.post('/api/navigation/items', { items }),
  },
  webhook: {
    getReceivers: () => api.get('/api/webhook/receivers'),
    createReceiver: (data: any) => api.post('/api/webhook/receivers', data),
    deleteReceiver: (id: string) => api.delete(`/api/webhook/receivers/${id}`),
    getLogs: (receiverId: string) => api.get(`/api/webhook/receivers/${receiverId}/logs`),
  },
  externalControl: {
    getConfig: () => api.get('/api/external-control/config'),
    updateConfig: (data: any) => api.post('/api/external-control/config', data),
  },
}
