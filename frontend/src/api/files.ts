import { api } from './client'

export const filesApi = {
  list: (path: string) => api.get('/api/files/list', { params: { path } }),
  read: (path: string) => api.get('/api/files/read', { params: { path } }),
  write: (path: string, content: string) => api.post('/api/files/write', { path, content }),
  delete: (path: string) => api.delete('/api/files/delete', { params: { path } }),
  mkdir: (path: string) => api.post('/api/files/mkdir', { path }),
}
