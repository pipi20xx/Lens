import { api } from './client'

export const tmdbApi = {
  search: (params: any) => api.get('/api/tmdb-lab/search', { params }),
  fetch: (params: any) => api.get('/api/tmdb-lab/fetch', { params }),
  fetchSeason: (params: any) => api.get('/api/tmdb-lab/fetch-season', { params }),
  fetchEpisode: (params: any) => api.get('/api/tmdb-lab/fetch-episode', { params }),
  lookup: (params: any) => api.get('/api/tmdb', { params }),
  searchById: (params: any) => api.post('/api/tmdb-search/search-by-id', params),
}
