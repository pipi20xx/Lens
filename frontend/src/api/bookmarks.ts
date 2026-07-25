import { api } from './client'

export const bookmarksApi = {
  list: () => api.get('/api/bookmarks/'),
  create: (data: any) => api.post('/api/bookmarks/', data),
  update: (id: number, data: any) => api.put(`/api/bookmarks/${id}`, data),
  delete: (id: number) => api.delete(`/api/bookmarks/${id}`),
  deleteAll: () => api.delete('/api/bookmarks/'),
  getDuplicates: () => api.get('/api/bookmarks/duplicates'),
  checkHealth: () => api.post('/api/bookmarks/check-health'),
  export: () => api.get('/api/bookmarks/export'),
  reorder: (ids: number[]) => api.post('/api/bookmarks/reorder', ids),
  aiAutoOrganize: (data: any) => api.post('/api/bookmarks/ai-auto-organize', data),
  importHtml: (file: File) => {
    const formData = new FormData()
    formData.append('file', file)
    return api.post('/api/bookmarks/import-html', formData)
  },
}
