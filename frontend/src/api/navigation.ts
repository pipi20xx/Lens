import { api } from './client'

export const navigationApi = {
  getItems: () => api.get('/api/navigation/items'),
  updateItems: (items: any[]) => api.post('/api/navigation/items', { items }),
  getGroups: () => api.get('/api/navigation/groups'),
  updateGroups: (groups: any[]) => api.post('/api/navigation/groups', { groups }),
}
