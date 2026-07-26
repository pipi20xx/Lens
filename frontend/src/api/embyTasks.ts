import { api } from './client'

export const embyTasksApi = {
  list: () => api.get('/api/emby-tasks'),
  run: (id: string) => api.post(`/api/emby-tasks/${id}/run`),
  stop: (id: string) => api.delete(`/api/emby-tasks/${id}/run`),
}
