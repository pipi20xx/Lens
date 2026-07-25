import { api } from './client'

export const embyApi = {
  getItemInfo: (params?: any) => api.get('/api/items/info', { params }),
  queryItems: (params?: any) => api.get('/api/items/query', { params }),
}
