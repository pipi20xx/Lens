import { api } from './client'

export const actorsApi = {
  getActors: (params?: any) => api.get('/api/actors', { params }),
  getActor: (id: string) => api.get(`/api/actors/${id}`),
  updateActor: (id: string, data: any) => api.put(`/api/actors/${id}`, data),
  deleteActor: (id: string) => api.delete(`/api/actors/${id}`),
  refreshActor: (id: string) => api.post(`/api/actors/${id}/refresh`),
}
