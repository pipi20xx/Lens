import { api } from './client'

export const embyTasksApi = {
  getTasks: () => api.get('/api/emby-tasks'),
  runTask: (id: string) => api.post(`/api/emby-tasks/${id}/run`),
  stopTask: (id: string) => api.delete(`/api/emby-tasks/${id}/run`),
}
