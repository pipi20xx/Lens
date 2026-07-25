import { api } from './client'

export const embyTasksApi = {
  getTasks: () => api.get('/api/emby/tasks'),
  runTask: (id: string) => api.post(`/api/emby/tasks/${id}/run`),
  getTaskStatus: (id: string) => api.get(`/api/emby/tasks/${id}/status`),
}
