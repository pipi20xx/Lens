import { api } from './client'

export const serverApi = {
  getServers: () => api.get('/api/server'),
  addServer: (data: any) => api.post('/api/server', data),
  updateServer: (id: string, data: any) => api.put(`/api/server/${id}`, data),
  deleteServer: (id: string) => api.delete(`/api/server/${id}`),
  activateServer: (id: string) => api.post(`/api/server/${id}/activate`),
}
