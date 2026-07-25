import { api } from './client'

export const embyApi = {
  getItems: (params?: any) => api.get('/api/emby/items', { params }),
  getItem: (id: string) => api.get(`/api/emby/items/${id}`),
  searchItems: (query: string) => api.get('/api/emby/items/search', { params: { query } }),
}
