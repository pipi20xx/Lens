import { api } from './client'

export const embyLibrariesApi = {
  getLibraries: () => api.get('/api/emby/libraries'),
  getLibrary: (id: string) => api.get(`/api/emby/libraries/${id}`),
  updateLibrary: (id: string, data: any) => api.put(`/api/emby/libraries/${id}`, data),
  refreshLibrary: (id: string) => api.post(`/api/emby/libraries/${id}/refresh`),
}
