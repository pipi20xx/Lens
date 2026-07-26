import { api } from './client'

export const actorsApi = {
  searchActors: (params: { keyword?: string; page?: number; page_size?: number }) =>
    api.get('/api/actors/search-emby', { params: { query: params.keyword } }),
  searchEmby: (query: string) => api.get('/api/actors/search-emby', { params: { query } }),
  searchTmdb: (query: string) => api.get('/api/actors/search-tmdb', { params: { query } }),
  refreshActor: (actorId: string) => api.get('/api/actors/search-emby', { params: { query: actorId } }),
  updateName: (embyId: string, newName: string) =>
    api.post('/api/actors/update-actor-name', { emby_id: embyId, new_name: newName }),
  syncActor: (embyId: string, data: any) =>
    api.post('/api/actors/update-emby-actor', { emby_id: embyId, data }),
}
