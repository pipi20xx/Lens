import { api } from './client'

export const tmdbApi = {
  search: (query: string, type?: string) => api.get('/api/tmdb/search', { params: { query, type } }),
  getDetails: (id: number, type: string) => api.get(`/api/tmdb/${type}/${id}`),
  reverseLookup: (name: string) => api.get('/api/tmdb/reverse-lookup', { params: { name } }),
  idSearch: (id: number, type: string) => api.get('/api/tmdb/id-search', { params: { id, type } }),
}
