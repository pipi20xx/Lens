import { api } from './client'

export const backupApi = {
  getBackups: () => api.get('/api/backup'),
  createBackup: (data: any) => api.post('/api/backup', data),
  restoreBackup: (id: string) => api.post(`/api/backup/${id}/restore`),
  deleteBackup: (id: string) => api.delete(`/api/backup/${id}`),
  downloadBackup: (id: string) => api.get(`/api/backup/${id}/download`),
  getEmbyBackups: () => api.get('/api/emby-config-backup'),
  createEmbyBackup: () => api.post('/api/emby-config-backup'),
  restoreEmbyBackup: (id: string) => api.post(`/api/emby-config-backup/${id}/restore`),
  deleteEmbyBackup: (id: string) => api.delete(`/api/emby-config-backup/${id}`),
}
